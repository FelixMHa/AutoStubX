

public class Benchmark3 {
    public static void main(String[] args) {
        // fetch input
        Long input_1_0 = Long.valueOf(args[0]);
        Long input_2_0 = Long.valueOf(args[1]);


        // Perform computation         
        Long output_1 = Long.reverse(input_1_0);
        Long output_2 = Long.reverse(input_2_0);

        
        // Compare output
        if (output_1 == 2558450033259184128L && output_2 == 1547747334048186367L) {
            System.out.println("Correct :)");
        } else {
            System.exit(1);
        }
    }
}

