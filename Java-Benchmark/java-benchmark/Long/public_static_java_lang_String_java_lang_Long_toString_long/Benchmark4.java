

public class Benchmark4 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        String output_1 = Long.toString(input_1_0);
        String output_2 = Long.toString(input_2_0);

        
        // Compare output
        if (output_1.equals("-173289547287344") && output_2.equals("1187080128")) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

