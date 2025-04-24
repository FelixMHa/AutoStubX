

public class Benchmark6 {
    public static void main(String[] args) {
        // fetch input
        Integer input_1_0 = Integer.valueOf(args[0]);
        Integer input_2_0 = Integer.valueOf(args[1]);


        // Perform computation         
        Integer output_1 = Character.toUpperCase(input_1_0);
        Integer output_2 = Character.toUpperCase(input_2_0);

        
        // Compare output
        if (output_1 == -729 && output_2 == -380) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

